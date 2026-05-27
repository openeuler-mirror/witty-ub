#include "urma_failure_497.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure497> g_urma("urma_497");

bool UrmaFailure497::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_eid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to open urma cdev with path' | grep -F ', dev_fd:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure497::GetName() const
{
    return "EID信息的sysfs读取或解析失败";
}

std::string UrmaFailure497::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始"
           "化。";
}

RootCause UrmaFailure497::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure497::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure497::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_eid，Failed to open urma cdev with path，, dev_fd:";
}

std::string UrmaFailure497::GetId() const
{
    return "urma_497";
}

} // namespace diag
