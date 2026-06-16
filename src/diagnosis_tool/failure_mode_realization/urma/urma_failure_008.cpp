#include "urma_failure_008.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure008> g_urma("urma_008");

bool UrmaFailure008::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfr_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to init active indices'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure008::GetName() const
{
    return "初始化JFR过程中依赖步骤失败";
}

std::string UrmaFailure008::GetRootCauseDesc() const
{
    return "函数用于初始化JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure008::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure008::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure008::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jfr_p_vjetty_info，Failed to init active indices。";
}

std::string UrmaFailure008::GetId() const
{
    return "urma_008";
}

} // namespace diag
