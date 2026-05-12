#include "urma_0080_bondp_add_jfs_p_vjetty_id_info_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure> g_urma("urma_0080");

bool Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0081"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::GetName() const
{
    return "bondp_add_jfs_p_vjetty_id_info 函数故障";
}

std::string Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0080BondpAddJfsPVjettyIdInfoFunctionFailure::GetId() const
{
    return "urma_0080";
}
} // namespace diag
