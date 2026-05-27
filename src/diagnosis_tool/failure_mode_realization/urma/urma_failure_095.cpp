#include "urma_failure_095.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure095> g_urma("urma_095");

bool UrmaFailure095::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'get_comp_urma_jetty_id' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to get_comp_urma_jetty, Invalid type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure095::GetName() const
{
    return "获取组件所需输入对象无效导致获取组件失败";
}

std::string UrmaFailure095::GetRootCauseDesc() const
{
    return "函数用于获取组件，调用方传入的获取组件所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure095::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure095::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure095::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_comp_urma_jetty_id，Failed to get_comp_urma_jetty, Invalid type:。";
}

std::string UrmaFailure095::GetId() const
{
    return "urma_095";
}

} // namespace diag
