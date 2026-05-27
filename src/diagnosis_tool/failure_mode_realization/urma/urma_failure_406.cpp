#include "urma_failure_406.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure406> g_urma("urma_406");

bool UrmaFailure406::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure406::GetName() const
{
    return "URMA context、provider操作表无效导致释放Token失败";
}

std::string UrmaFailure406::GetRootCauseDesc() const
{
    return "函数用于释放Token，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure406::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure406::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure406::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_token_id，Invalid parameter.。";
}

std::string UrmaFailure406::GetId() const
{
    return "urma_406";
}

} // namespace diag
