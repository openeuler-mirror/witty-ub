#include "urma_failure_196.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure196> g_urma("urma_196");

bool UrmaFailure196::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_jfc' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure196::GetName() const
{
    return "URMA context、设备对象、JFR对象无效导致创建Jetty失败";
}

std::string UrmaFailure196::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，调用方传入的URMA "
           "context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure196::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure196::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure196::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，Invalid parameter.。";
}

std::string UrmaFailure196::GetId() const
{
    return "urma_196";
}

} // namespace diag
