#include "urma_failure_671.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure671> g_urma("urma_671");

bool UrmaFailure671::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to delete jfr, dev_name:' | grep -F ', eid_idx:' | grep -F ', id:' | "
        "grep -F ', status:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure671::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure671::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure671::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure671::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure671::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfr，[DRV_ERR]Failed to delete jfr, dev_name:，, eid_idx:，, id:，, "
           "status:";
}

std::string UrmaFailure671::GetId() const
{
    return "urma_671";
}

} // namespace diag
