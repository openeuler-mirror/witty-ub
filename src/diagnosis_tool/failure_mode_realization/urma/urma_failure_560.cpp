#include "urma_failure_560.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure560> g_urma("urma_560");

bool UrmaFailure560::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'convert_jfs_vwr_to_pwr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Unsupported send opcode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure560::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure560::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure560::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure560::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure560::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：convert_jfs_vwr_to_pwr，Unsupported send opcode";
}

std::string UrmaFailure560::GetId() const
{
    return "urma_560";
}

} // namespace diag
