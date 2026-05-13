#include "urma_1083_deepcopy_sg_function_failure_bond_utils_wr_utils_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC> g_urma("urma_1083");

bool Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1084", "urma_1085"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetName() const
{
    return "deepcopy_sg 函数故障（bond/utils/wr_utils.c）";
}

std::string Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1083DeepcopySgFunctionFailureBondUtilsWrUtilsC::GetId() const
{
    return "urma_1083";
}
} // namespace diag
