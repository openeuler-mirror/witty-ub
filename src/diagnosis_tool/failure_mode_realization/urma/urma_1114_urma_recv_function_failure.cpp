#include "urma_1114_urma_recv_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1114UrmaRecvFunctionFailure> g_urma("urma_1114");

bool Urma1114UrmaRecvFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1115", "urma_1116"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1114UrmaRecvFunctionFailure::GetName() const
{
    return "urma_recv 函数故障";
}

std::string Urma1114UrmaRecvFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1114UrmaRecvFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1114UrmaRecvFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1114UrmaRecvFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1114UrmaRecvFunctionFailure::GetId() const
{
    return "urma_1114";
}
} // namespace diag
