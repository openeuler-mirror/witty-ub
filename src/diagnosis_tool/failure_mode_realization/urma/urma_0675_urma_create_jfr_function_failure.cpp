#include "urma_0675_urma_create_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0675UrmaCreateJfrFunctionFailure> g_urma("urma_0675");

bool Urma0675UrmaCreateJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0676", "urma_0677", "urma_0678", "urma_0679"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0675UrmaCreateJfrFunctionFailure::GetName() const
{
    return "urma_create_jfr 函数故障";
}

std::string Urma0675UrmaCreateJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0675UrmaCreateJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0675UrmaCreateJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0675UrmaCreateJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0675UrmaCreateJfrFunctionFailure::GetId() const
{
    return "urma_0675";
}
} // namespace diag
