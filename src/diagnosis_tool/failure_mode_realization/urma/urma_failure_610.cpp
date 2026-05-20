#include "urma_failure_610.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure610> g_urma("urma_610");

bool UrmaFailure610::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to free token_id, dev_name:' | "
        "grep -F ', eid_idx:' | "
        "grep -F ', tid:' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure610::GetName() const
{
    return "urma_free_token_id 执行释放 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure610::GetRootCauseDesc() const
{
    return "urma_free_token_id 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure610::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure610::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure610::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Failed to free token_id, dev_name: , eid_idx: , tid: , ret";
}

std::string UrmaFailure610::GetId() const
{
    return "urma_610";
}

} // namespace diag
