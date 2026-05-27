#include "urma_failure_320.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure320> g_urma("urma_320");

bool UrmaFailure320::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_post_jetty_recv_wr' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure320::GetName() const
{
    return "Jetty对象、WR对象无效导致投递Jetty失败";
}

std::string UrmaFailure320::GetRootCauseDesc() const
{
    return "函数用于投递Jetty，调用方传入的Jetty对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure320::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure320::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure320::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jetty_recv_wr，Invalid parameter.。";
}

std::string UrmaFailure320::GetId() const
{
    return "urma_320";
}

} // namespace diag
