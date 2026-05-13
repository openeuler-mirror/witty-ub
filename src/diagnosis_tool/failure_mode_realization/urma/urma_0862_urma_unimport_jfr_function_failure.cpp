#include "urma_0862_urma_unimport_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0862UrmaUnimportJfrFunctionFailure> g_urma("urma_0862");

bool Urma0862UrmaUnimportJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0863"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0862UrmaUnimportJfrFunctionFailure::GetName() const
{
    return "urma_unimport_jfr 函数故障";
}

std::string Urma0862UrmaUnimportJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0862UrmaUnimportJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0862UrmaUnimportJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0862UrmaUnimportJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0862UrmaUnimportJfrFunctionFailure::GetId() const
{
    return "urma_0862";
}
} // namespace diag
