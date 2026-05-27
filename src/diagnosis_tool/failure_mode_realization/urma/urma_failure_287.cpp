#include "urma_failure_287.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure287> g_urma("urma_287");

bool UrmaFailure287::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->deactive_jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure287::GetName() const
{
    return "去激活Jetty过程中依赖步骤失败";
}

std::string UrmaFailure287::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure287::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure287::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure287::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Failed to exec ops->deactive_jetty.。";
}

std::string UrmaFailure287::GetId() const
{
    return "urma_287";
}

} // namespace diag
