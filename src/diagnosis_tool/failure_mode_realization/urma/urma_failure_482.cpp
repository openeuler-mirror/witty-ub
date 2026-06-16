#include "urma_failure_482.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure482> g_urma("urma_482");

bool UrmaFailure482::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'read_eid_sysfs_with_index' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to parse eid value, dev name:' | grep -F ', eid idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure482::GetName() const
{
    return "EID信息的sysfs读取或解析失败";
}

std::string UrmaFailure482::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始"
           "化。";
}

RootCause UrmaFailure482::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure482::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure482::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_sysfs_with_index，Failed to parse eid value, dev name:，, eid "
           "idx:。";
}

std::string UrmaFailure482::GetId() const
{
    return "urma_482";
}

} // namespace diag
