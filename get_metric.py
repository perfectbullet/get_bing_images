import os


def metric_by_name():
    metric_dir = 'images/'
    for d in os.listdir(metric_dir):
        count_num = 0
        for root, dirs, files in os.walk(os.path.join(metric_dir, d)):
            for file in files:
                count_num += 1
        print(f'{d} has {count_num} images')



def metric_total(dir_path):
    count_num = 0
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            count_num += 1
    print(f'{dir_path} has {count_num} images')


if __name__ == '__main__':
    metric_total('./images/天然矿物')
