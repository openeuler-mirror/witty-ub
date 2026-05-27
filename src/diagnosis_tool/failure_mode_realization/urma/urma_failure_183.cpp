#include "urma_failure_183.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure183> g_urma("urma_183");

bool UrmaFailure183::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_trans_mode' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'UB dev should use share jfr!'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure183::GetName() const
{
    return "创建设备过程中依赖步骤失败";
}

std::string UrmaFailure183::GetRootCauseDesc() const
{
    return "函数用于创建设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure183::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure183::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure183::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，UB dev should use share jfr!。";
}

std::string UrmaFailure183::GetId() const
{
    return "urma_183";
}

} // namespace diag
