#include "urma_failure_332.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure332> g_urma("urma_332");

bool UrmaFailure332::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_recv_wr_and_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to allocate jfr wr entry'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure332::GetName() const
{
    return "JFR相关临时结构或命令参数分配失败";
}

std::string UrmaFailure332::GetRootCauseDesc() const
{
    return "函数在投递JFR前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure332::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure332::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure332::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_post_recv_wr_and_store，Failed to allocate jfr wr entry";
}

std::string UrmaFailure332::GetId() const
{
    return "urma_332";
}

} // namespace diag
