#include "urma_failure_472.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure472> g_urma("urma_472");

bool UrmaFailure472::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_read_sysfs_file' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed open file:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure472::GetName() const
{
    return "设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败";
}

std::string UrmaFailure472::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导"
           "致URMA无法完成设备发现或能力初始化。";
}

RootCause UrmaFailure472::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure472::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure472::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_read_sysfs_file，Failed open file:，, errno:";
}

std::string UrmaFailure472::GetId() const
{
    return "urma_472";
}

} // namespace diag
