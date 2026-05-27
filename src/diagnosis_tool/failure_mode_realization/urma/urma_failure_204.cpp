#include "urma_failure_204.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure204> g_urma("urma_204");

bool UrmaFailure204::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jetty still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure204::GetName() const
{
    return "释放Jetty过程中依赖步骤失败";
}

std::string UrmaFailure204::GetRootCauseDesc() const
{
    return "函数用于释放Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure204::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure204::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure204::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，jetty still actived, please deactived first。";
}

std::string UrmaFailure204::GetId() const
{
    return "urma_204";
}

} // namespace diag
