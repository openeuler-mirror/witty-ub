#include "urma_failure_005.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure005> g_urma("urma_005");

bool UrmaFailure005::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init jfs wr buf'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure005::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure005::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure005::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure005::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure005::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfs_p_vjetty_info，Failed to init jfs wr buf";
}

std::string UrmaFailure005::GetId() const
{
    return "urma_005";
}

} // namespace diag
