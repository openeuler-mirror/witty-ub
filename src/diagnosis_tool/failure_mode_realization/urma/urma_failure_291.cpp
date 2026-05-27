#include "urma_failure_291.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure291> g_urma("urma_291");

bool UrmaFailure291::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'max_jetty_in_jetty_grp' | grep -F 'is err.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure291::GetName() const
{
    return "确认Jetty过程中依赖步骤失败";
}

std::string UrmaFailure291::GetRootCauseDesc() const
{
    return "函数用于确认Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure291::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure291::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure291::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，max_jetty_in_jetty_grp，is err.。";
}

std::string UrmaFailure291::GetId() const
{
    return "urma_291";
}

} // namespace diag
