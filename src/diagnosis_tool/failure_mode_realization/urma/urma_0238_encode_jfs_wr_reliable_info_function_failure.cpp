#include "urma_0238_encode_jfs_wr_reliable_info_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0238EncodeJfsWrReliableInfoFunctionFailure> g_urma("urma_0238");

bool Urma0238EncodeJfsWrReliableInfoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0239"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0238EncodeJfsWrReliableInfoFunctionFailure::GetName() const
{
    return "encode_jfs_wr_reliable_info 函数故障";
}

std::string Urma0238EncodeJfsWrReliableInfoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0238EncodeJfsWrReliableInfoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0238EncodeJfsWrReliableInfoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0238EncodeJfsWrReliableInfoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0238EncodeJfsWrReliableInfoFunctionFailure::GetId() const
{
    return "urma_0238";
}
} // namespace diag
