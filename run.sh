
BENCHMARK=$1

./cvc4_master --bitblast=eager -d cnf $BENCHMARK.smt2 &> $BENCHMARK.map
./cvc4_master --bitblast=eager -d sat::minisat $BENCHMARK.smt2 &> $BENCHMARK.out

echo "Generated SAT queries"
# ./cnf.py --cnf-trans --nominal $BENCHMARK.map litmap

pypy3 cnf.py --cnf-trans $BENCHMARK.map litmap
pypy3 cnf.py $BENCHMARK.out $BENCHMARK.dimacs

picosat -T $BENCHMARK.trace $BENCHMARK.dimacs
# tracecheck -B $BENCHMARK.proof $BENCHMARK.trace
# pypy3 proc_data.py --resproof $BENCHMARK.proof
./learning.py $BENCHMARK.trace $BENCHMARK.dimacs model_knr.pkl KNR

echo "Now run"
echo "./clausegen.py <model_file> <next bound dimacs file> <output file>"
echo "Then compare the times"

# when using proc_data.py, produces data file named data.arff
# echo "Data available in data.arff"
