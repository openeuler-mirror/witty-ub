#include "urma_failure_797.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure797> g_urma("urma_797");

bool UrmaFailure797::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F '[DRV_ERR]Failed to delete jetty, dev_name: , eid_idx: , id: , ret')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure797::GetName() const
{
    return "urma_delete_jetty 执行删除 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure797::GetRootCauseDesc() const
{
    return "urma_delete_jetty 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure797::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure797::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure797::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Failed to delete jetty, dev_name: , eid_idx: , id: , ret";
}

std::string UrmaFailure797::GetId() const
{
    return "urma_797";
}

} // namespace diag
