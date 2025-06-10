import matplotlib.pyplot as plt
import numpy as np

filepath = "solving-times.txt"

def main():

    sizes = []
    times = []
    with open(filepath, "r") as f:
        for line in f:
            size, time = line.split(',')
            size,time = int(size), float(time) * 1000
            times.append(time)
            sizes.append(size)

    data = list(zip(sizes, times))
    data.sort(key=lambda x: x[1])
    print(data[-1])
    data = data[:-1]



    sizes, times = zip(*data)


    plt.title('Solving Time vs. Puzzle Size')
    plt.xlabel('Puzzle size (w*h)')
    plt.ylabel('Time (ms)')
    plt.xlim(0, max(max(sizes), int(max(times))))
    plt.ylim(0, max(max(sizes), int(max(times))))

    plt.scatter(sizes, times)
    plt.plot(np.unique(sizes), np.poly1d(np.polyfit(sizes, times, 1))(np.unique(sizes)), color="pink")

    plt.savefig('solving-times.png')
    plt.show()

if __name__ == '__main__':
    main()