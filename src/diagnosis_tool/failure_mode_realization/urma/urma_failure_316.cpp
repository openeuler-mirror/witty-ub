#include "urma_failure_316.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure316> g_urma("urma_316");

bool UrmaFailure316::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_parse_rsvd_jetty_range' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'parse rsvd jetty:' | grep -F 'failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure316::GetName() const
{
    return "端口信息的sysfs读取或解析失败";
}

std::string UrmaFailure316::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取端口信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始"
           "化。";
}

RootCause UrmaFailure316::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure316::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure316::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_parse_rsvd_jetty_range，parse rsvd jetty:，failed";
}

std::string UrmaFailure316::GetId() const
{
    return "urma_316";
}

} // namespace diag
