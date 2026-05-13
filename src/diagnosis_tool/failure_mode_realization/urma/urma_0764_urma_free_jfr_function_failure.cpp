#include "urma_0764_urma_free_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0764UrmaFreeJfrFunctionFailure> g_urma("urma_0764");

bool Urma0764UrmaFreeJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0765", "urma_0766", "urma_0767"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0764UrmaFreeJfrFunctionFailure::GetName() const
{
    return "urma_free_jfr 函数故障";
}

std::string Urma0764UrmaFreeJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0764UrmaFreeJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0764UrmaFreeJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0764UrmaFreeJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0764UrmaFreeJfrFunctionFailure::GetId() const
{
    return "urma_0764";
}
} // namespace diag
