#include "urma_failure_297.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure297> g_urma("urma_297");

bool UrmaFailure297::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_grp' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter: jetty_list'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure297::GetName() const
{
    return "URMA context、provider操作表无效导致删除Jetty失败";
}

std::string UrmaFailure297::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure297::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure297::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure297::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，Invalid parameter: jetty_list。";
}

std::string UrmaFailure297::GetId() const
{
    return "urma_297";
}

} // namespace diag
