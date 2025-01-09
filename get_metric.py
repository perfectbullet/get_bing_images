import os

if __name__ == '__main__':
    metric_dir = 'images/世界前十战斗机'
    count_num = 0
    for root, dirs, files in os.walk(metric_dir):
        for file in files:
            count_num += 1
    print(f'{metric_dir} has {count_num} images')
