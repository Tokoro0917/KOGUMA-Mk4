#!/bin/bash
# make_case.py で作った計算のフォルダで、メッシュを作って解く(OpenFOAM v1912、4 並列)
# (このパッケージの OpenFOAM は、関数オブジェクト(forces など)が sha1 のエラーで止まるので使わない。結果は post.py で出す)
# 使い方: bash docs/calc/fan_cfd/run_case.sh <計算のフォルダ> [くり返しの数]
set -e
cd "$1"
export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
export WM_PROJECT_DIR=/usr/share/openfoam   # Ubuntu の openfoam パッケージの etc の場所
if [ -n "$2" ]; then
  foamDictionary -entry endTime -set "$2" system/controlDict > /dev/null
  foamDictionary -entry writeInterval -set "$(( $2 / 3 ))" system/controlDict > /dev/null   # 終わりの回数で必ず書き出すように、3 等分
fi
blockMesh > log.blockMesh 2>&1
surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
decomposePar -force > log.decomposePar0 2>&1
mpirun -np 4 snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
reconstructParMesh -constant > log.reconstructParMesh 2>&1
rm -rf processor*
topoSet > log.topoSet 2>&1
checkMesh > log.checkMesh 2>&1 || true
rm -rf 0 && cp -r 0.orig 0
decomposePar -force > log.decomposePar 2>&1
mpirun -np 4 simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
echo done
