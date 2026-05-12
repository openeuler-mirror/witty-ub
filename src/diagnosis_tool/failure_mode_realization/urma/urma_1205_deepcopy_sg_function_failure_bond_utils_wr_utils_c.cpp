#include "urma_1205_deepcopy_sg_function_failure_bond_utils_wr_utils_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC> g_urma("urma_1205");

bool Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1206"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetName() const
{
    return "deepcopy_sg 函数故障（bond/utils/wr_utils.c）";
}

std::string Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1205DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetId() const
{
    return "urma_1205";
}
} // namespace diag
