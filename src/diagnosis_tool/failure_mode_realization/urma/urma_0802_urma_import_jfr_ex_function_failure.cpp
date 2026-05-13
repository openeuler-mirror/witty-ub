#include "urma_0802_urma_import_jfr_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0802UrmaImportJfrExFunctionFailure> g_urma("urma_0802");

bool Urma0802UrmaImportJfrExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0803"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0802UrmaImportJfrExFunctionFailure::GetName() const
{
    return "urma_import_jfr_ex 函数故障";
}

std::string Urma0802UrmaImportJfrExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0802UrmaImportJfrExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0802UrmaImportJfrExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0802UrmaImportJfrExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0802UrmaImportJfrExFunctionFailure::GetId() const
{
    return "urma_0802";
}
} // namespace diag
