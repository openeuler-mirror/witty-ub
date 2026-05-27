#include "urma_failure_659.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure659> g_urma("urma_659");

bool UrmaFailure659::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to delete jfs, dev_name:' | grep -F ', eid_idx:' | grep -F ', id:' | grep -F ', "
        "ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure659::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure659::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure659::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure659::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure659::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfs，[DRV_ERR]Failed to delete jfs, dev_name:，, eid_idx:，, id:，, "
           "ret:";
}

std::string UrmaFailure659::GetId() const
{
    return "urma_659";
}

} // namespace diag
