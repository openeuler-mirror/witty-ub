#include "urma_failure_010.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure010> g_urma("urma_010");

bool UrmaFailure010::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to init active indices'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure010::GetName() const
{
    return "初始化Jetty过程中依赖步骤失败";
}

std::string UrmaFailure010::GetRootCauseDesc() const
{
    return "函数用于初始化Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure010::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure010::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure010::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Failed to init active indices。";
}

std::string UrmaFailure010::GetId() const
{
    return "urma_010";
}

} // namespace diag
