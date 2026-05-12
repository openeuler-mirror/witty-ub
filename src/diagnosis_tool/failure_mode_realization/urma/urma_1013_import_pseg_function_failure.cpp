#include "urma_1013_import_pseg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1013ImportPsegFunctionFailure> g_urma("urma_1013");

bool Urma1013ImportPsegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1014"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1013ImportPsegFunctionFailure::GetName() const
{
    return "import_pseg 函数故障";
}

std::string Urma1013ImportPsegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1013ImportPsegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1013ImportPsegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1013ImportPsegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1013ImportPsegFunctionFailure::GetId() const
{
    return "urma_1013";
}
} // namespace diag
