#include "urma_failure_037.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure037> g_urma("urma_037");

bool UrmaFailure037::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'init_create_jetty_cmd' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure037::GetName() const
{
    return "JFR对象无效导致初始化Jetty失败";
}

std::string UrmaFailure037::GetRootCauseDesc() const
{
    return "函数用于初始化Jetty，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure037::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure037::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure037::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_create_jetty_cmd，Invalid parameter。";
}

std::string UrmaFailure037::GetId() const
{
    return "urma_037";
}

} // namespace diag
