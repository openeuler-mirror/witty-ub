#include "urma_failure_090.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure090> g_urma("urma_090");

bool UrmaFailure090::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_bind_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'No valid active slice to bind'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure090::GetName() const
{
    return "未找到可用于激活Jetty的有效对象或路由";
}

std::string UrmaFailure090::GetRootCauseDesc() const
{
    return "函数在激活Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure090::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure090::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure090::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_bind_jetty，No valid active slice to bind。";
}

std::string UrmaFailure090::GetId() const
{
    return "urma_090";
}

} // namespace diag
