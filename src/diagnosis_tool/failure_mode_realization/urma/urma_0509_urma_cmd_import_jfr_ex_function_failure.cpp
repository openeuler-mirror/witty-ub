#include "urma_0509_urma_cmd_import_jfr_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0509UrmaCmdImportJfrExFunctionFailure> g_urma("urma_0509");

bool Urma0509UrmaCmdImportJfrExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0510"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0509UrmaCmdImportJfrExFunctionFailure::GetName() const
{
    return "urma_cmd_import_jfr_ex 函数故障";
}

std::string Urma0509UrmaCmdImportJfrExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0509UrmaCmdImportJfrExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0509UrmaCmdImportJfrExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0509UrmaCmdImportJfrExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0509UrmaCmdImportJfrExFunctionFailure::GetId() const
{
    return "urma_0509";
}
} // namespace diag
