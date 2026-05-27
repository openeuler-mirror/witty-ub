#include "urma_failure_208.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure208> g_urma("urma_208");

bool UrmaFailure208::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jetty still deactived, can not delete.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure208::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure208::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure208::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure208::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure208::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty，jetty still deactived, can not delete.。";
}

std::string UrmaFailure208::GetId() const
{
    return "urma_208";
}

} // namespace diag
