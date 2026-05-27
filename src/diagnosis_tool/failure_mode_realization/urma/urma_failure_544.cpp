#include "urma_failure_544.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure544> g_urma("urma_544");

bool UrmaFailure544::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'post_send_check_jfs_wr_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'when set write_wr, either of src/dst num_sge/sge has been set zero or NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure544::GetName() const
{
    return "WR数据通路处理失败";
}

std::string UrmaFailure544::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure544::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure544::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure544::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：post_send_check_jfs_wr_valid，when set write_wr, either of src/dst num_sge/sge "
           "has been set zero or NULL.";
}

std::string UrmaFailure544::GetId() const
{
    return "urma_544";
}

} // namespace diag
