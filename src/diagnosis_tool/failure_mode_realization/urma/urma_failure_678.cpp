#include "urma_failure_678.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure678> g_urma("urma_678");

bool UrmaFailure678::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]Failed to delete jfr, dev_name:' | grep -F ', eid_idx:' | grep -F ', id:' | grep -F ', status:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure678::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure678::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure678::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure678::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure678::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr，[DRV_ERR]Failed to delete jfr, dev_name:，, "
           "eid_idx:，, id:，, status:。";
}

std::string UrmaFailure678::GetId() const
{
    return "urma_678";
}

} // namespace diag
