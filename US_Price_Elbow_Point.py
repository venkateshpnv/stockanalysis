import sys
import DB

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid arguments")
        print("$ %s symbol" %(sys.argv[0]))
        sys.exit(1)

    DB.get_price_elbow_point(sys.argv[1])
