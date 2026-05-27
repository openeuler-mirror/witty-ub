#include "urma_failure_093.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure093> g_urma("urma_093");

bool UrmaFailure093::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'get_comp_urma_jetty_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get_comp_urma_jetty, Invalid type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure093::GetName() const
{
    return "获取组件所需输入对象无效导致获取组件失败";
}

std::string UrmaFailure093::GetRootCauseDesc() const
{
    return "函数用于获取组件，调用方传入的获取组件所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure093::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure093::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure093::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：get_comp_urma_jetty_id，Failed to get_comp_urma_jetty, Invalid type:";
}

std::string UrmaFailure093::GetId() const
{
    return "urma_093";
}

} // namespace diag
