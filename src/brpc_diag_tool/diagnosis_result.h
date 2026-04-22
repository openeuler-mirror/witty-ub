#include <string>

namespace brpc {
using namespace std;
class DiagnosisResult {
public:
    string result;
    void OutputResult();
};
}

/*
    规范：在本文件中定义诊断结果类型，即DiagnosisEngine.diagnosis的返回值类型。主要包含:
    1、数据：诊断结果数据，本样例中为字符串result；
    2、输出函数：输出诊断结果，会在结束诊断后被调用，本样例中在OutputResult中定义，打印result。
*/