#include "urma_failure_606.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure606> g_urma("urma_606");

bool UrmaFailure606::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_import_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to import seg, dev_name:' | "
        "grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure606::GetName() const
{
    return "urma_import_seg 执行导入 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure606::GetRootCauseDesc() const
{
    return "urma_import_seg 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure606::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure606::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure606::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Failed to import seg, dev_name: , eid_idx";
}

std::string UrmaFailure606::GetId() const
{
    return "urma_606";
}

} // namespace diag
