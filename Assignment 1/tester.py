import subprocess
import os


directory_path = './'
python ="python3"

f = './graph.py'
print("---------------------")
# print(f"python {f} --create_random_graph 30 1.01 --multi_BFS 0 5 20 --plot --output final_graph.gml")
print("---------------------")
# subprocess.run([python, f, "--create_random_graph",  "30", "1.01", "--multi_BFS", "0", "5", "20", "--plot", "--output", "final_graph.gml"])

# print(f"python {f} --input final_graph.gml --analyze")
# print("---------------------")
# subprocess.run([python, f, "--input",  "final_graph.gml", "--analyze"])

print(f"python {f} --create_random_graph 10 0.5 --plot --analyze")
print("---------------------")
subprocess.run([python, f, "--create_random_graph",  "10", "0.5", "--plot", "--analyze"])

