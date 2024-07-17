import matplotlib
import numpy as np
from scipy.spatial.distance import cdist

matplotlib.use("Agg")
import argparse
import datetime
import glob
import logging
import os
import sys
import shutil
import subprocess
from pathlib import Path
from calorine.gpumd import *
from calorine.nep import get_descriptors
from ase.io import read as ase_read
from ase.io import write as ase_write
import matplotlib.pyplot as plt
from monty.os import cd
from sklearn.decomposition import PCA

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout  # 指定输出流为sys.stdout
)
# 这里是间距  每隔NumSamples 抽取一个
# 因为我是每1000步输出一个 跑1ns 一共也就100个数据  所以我设置2 抽取50
NumSamples = 2


# 从pynep复制的最远点采样 就使用这一个函数 因为安装不方便
def select(new_data, now_data=[], min_distance=None, min_select=1, max_select=None):
    """Select those data fartheset from given data
    
    Args:
        new_data (2d list or array): A series of points to be selected
        now_data (2d list or array): Points already in the dataset.
            Defaults to []. (No existed data)
        min_distance (float, optional):
            If distance between two points exceeded the minimum distance, stop the selection.
            Defaults to None (use the self.min_distance)
        min_select (int, optional): Minimal numbers of points to be selected. This may cause
            some distance between points less than given min_distance.
            Defaults to 1.
        max_select (int, optional): Maximum numbers of points to be selected.
            Defaults to None. (No limitation)

    Returns:
        A list of int: index of selected points
    """
    metric = 'euclidean'
    metric_para = {}
    min_distance = min_distance
    max_select = max_select or len(new_data)
    to_add = []
    if len(new_data) == 0:
        return to_add
    if len(now_data) == 0:
        to_add.append(0)
        now_data.append(new_data[0])
    distances = np.min(cdist(new_data, now_data, metric=metric, **metric_para), axis=1)

    while np.max(distances) > min_distance or len(to_add) < min_select:
        i = np.argmax(distances)
        to_add.append(i)
        if len(to_add) >= max_select:
            break
        distances = np.minimum(distances, cdist([new_data[i]], new_data, metric=metric)[0])
    return to_add


def run(run_cmd: str, run_dir: Path):
    start = datetime.datetime.now()
    logging.info("\t开始计算")

    vasp_cmd = [os.path.expanduser(os.path.expandvars(run_cmd))]
    with cd(run_dir), open(f"{run_cmd}.out", "w") as f_std, open(f"{run_cmd}.err", "w", buffering=1) as f_err:
        subprocess.check_call(vasp_cmd, stdout=f_std, stderr=f_err)
    logging.info("\t计算完成" + f"\t耗时：{datetime.datetime.now() - start}")


def remove_garbage_structure(atoms_list):
    # 删除跑崩溃的结构
    result = []
    for atoms in atoms_list:
        postion = atoms.get_all_distances()
        if (np.min(postion[postion > 0])) < 1:
            continue
        result.append(atoms)

    return result


def verify_path(path: Path) -> None:
    """
    会检查是否存在路径，若不存在，则创建该路径，支持多级目录创建
    :param path:
    :return:
    """
    if not path.exists():
        # path.mkdir()
        os.makedirs(path)


def cp_file(source_file: Path, destination_dir: Path) -> None:
    """
    复制文件
    :param source_file: 要复制的文件
    :param destination_dir: 希望复制到的路径
    :return:
    """
    src_files = glob.glob(source_file.as_posix())
    for i in src_files:
        logging.debug(f"\t复制文件：{i} -> {destination_dir.as_posix()}")
        shutil.copy(i, destination_dir.as_posix())
    return


def iter_path(glob_strs: list):
    def decorator(func):
        def wrapper(path: Path | str, *args, **kwargs):
            if isinstance(path, str):
                path = Path(path)
            if path.is_dir():
                parent = path
            else:
                parent = path.parent
            result =[]
            for glob_str in glob_strs:

                for i in parent.glob(glob_str):
                    if path.is_file():
                        if i.name != path.name:
                            continue

                    try:
                        result.append(func(i, *args, **kwargs))
                    except KeyboardInterrupt:
                        return
                    except Exception as e:
                        logging.error(e)
                        pass
            return result
        return wrapper

    return decorator


@iter_path(["*.xyz", "*.vasp"])
def molecular_dynamics(path: Path, temperature, run_time):
    """
    根据指定的文件夹 以此计算文件夹下的所有的xyz文件

    :param self:
    :return:
    """

    if path.suffix == ".vasp":
        atoms = ase_read(path, 0, format="vasp")

    else:
        atoms = ase_read(path, 0, format="extxyz")
    md_path = root_path.joinpath(f"cache/{atoms.symbols}/{run_time}/md-{temperature}k")
    verify_path(md_path)
    logging.info(f"路径：{md_path.as_posix()}")

    run_in = [('potential', 'nep.txt'),
              ('velocity', temperature),
              ('ensemble', ('nvt_nhc', temperature, temperature, '100')),
              ('time_step', 1.0),
              ('dump_thermo', 1000),
              ('dump_exyz', ('1000', '0', '0')),
              ('run', 1000 * run_time)]

    write_runfile(md_path.joinpath("run.in"), run_in)
    # cp_file(root_path.joinpath("run.in"), md_path.joinpath("run.in"))
    cp_file(root_path.joinpath("nep.txt"), md_path.joinpath("nep.txt"))
    atoms.write(md_path.joinpath("model.xyz"), format="extxyz")
    run("gpumd", md_path)

    data = read_thermo(md_path.joinpath("thermo.out").as_posix(), len(atoms))

    potential_energy = data.potential_energy.to_numpy(dtype='float')

    fig = plt.figure()
    plt.plot(list(range(potential_energy.shape[0])), potential_energy)
    plt.savefig(md_path.joinpath("md_energy.png"), dpi=150)

    return md_path


def select_structures(train, new: Path, max_selected=20):
    # 首先去掉跑崩溃的结构

    new_atoms = ase_read(new, ":", format="extxyz")

    new_atoms = remove_garbage_structure(new_atoms)

    train_des = np.array([np.mean(get_descriptors(i, "nep.txt"), axis=0) for i in train])

    new_des = np.array([np.mean(get_descriptors(i, "nep.txt"), axis=0) for i in new_atoms])

    selected_i = select(np.vstack([train_des, new_des]), train_des, min_distance=0.01, max_select=max_selected,
                        min_select=0)
    # 画一下图

    reducer = PCA(n_components=2)
    reducer.fit(new_des)
    proj = reducer.transform(new_des)
    fig = plt.figure()
    plt.scatter(proj[:, 0], proj[:, 1], label='all data')

    if selected_i:
        selected_proj = reducer.transform(np.array([new_des[i - train_des.shape[0]] for i in selected_i]))
        plt.scatter(selected_proj[:, 0], selected_proj[:, 1], label='selected data')
    plt.legend()
    plt.axis('off')

    plt.savefig(new.with_name('select.png'))
    return [new_atoms[i - train_des.shape[0]] for i in selected_i]


def auto_learn():
    """
    主动学习迭代
    首先要有一个nep.txt nep.in train.xyz
    :return:
    """
    # 定义迭代时间 单位ps
    times = [10000]
    temperatures = range(50, 1000, 50)
    trainxyz = ase_read("train.xyz", ":", format="extxyz")
    for epoch, run_time in enumerate(times):
        logging.info(f"开始第{epoch + 1}次主动学习，采样时长：{run_time} ps。")
        # 存放每次epoch 新增的训练集
        new_atoms = []
        # 进行gpumd采样
        for temperature in temperatures:
            # 对每个温度进行采样
            logging.info(f"GPUMD采样中，温度：{temperature}k。时长：{run_time}ps")

            md_paths = molecular_dynamics("./s/", temperature=temperature, run_time=run_time)
            # 筛选出结构
            for md_path in md_paths:

                selected = select_structures(trainxyz, md_path.joinpath("dump.xyz"), max_selected=20)
                logging.info(f"得到{len(selected)}个结构")
                for i, atom in enumerate(selected):
                    atom.info["Config_type"] = f"epoch-{epoch + 1}-{run_time}ps-{temperature}k-{i + 1}"
                new_atoms.extend(selected)
        logging.info(f"本次主动学习新增了{len(new_atoms)}个结构。")

        ase_write(root_path.joinpath(f"result/learn-epoch-{epoch}-{run_time}ps.xyz"), new_atoms, format="extxyz")
        break
        #然后nep训练


def prediction(self):
    pass


def build_argparse():
    parser = argparse.ArgumentParser(description="""GPUMD 工具. 
        可以批量md和主动学习 """,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_subparsers()

    parser.add_argument(
        "job_type", choices=["prediction", "md", "learn"], help=" "
    )
    parser.add_argument(
        "path", type=Path, help="要计算的xyz路径，或者要批量计算的文件夹。"
    )

    return parser


if __name__ == '__main__':
    # 采样
    parser = build_argparse()
    args = parser.parse_args()

    if not os.path.exists("./result"):
        os.mkdir("./result")
    root_path = Path("./")

    if args.job_type == "md":
        for t in range(50, 1000, 50):
            molecular_dynamics(args.path, temperature=t)
    elif args.job_type == "prediction":
        prediction(args.path)
    elif args.job_type == "learn":
        auto_learn()