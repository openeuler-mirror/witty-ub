#include "urma_1153_urma_free_token_id_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1153UrmaFreeTokenIdResourceFailure> g_urma("urma_1153");

bool Urma1153UrmaFreeTokenIdResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Failed to free token_id, dev_name: %, eid_idx: %, tid: %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1153UrmaFreeTokenIdResourceFailure::GetName() const
{
    return "urma_free_token_id 释放资源失败";
}

std::string Urma1153UrmaFreeTokenIdResourceFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1153UrmaFreeTokenIdResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1153UrmaFreeTokenIdResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1153UrmaFreeTokenIdResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to free token_id, dev_name: %, eid_idx: %, tid: "
           "%, ret: %.";
}

std::string Urma1153UrmaFreeTokenIdResourceFailure::GetId() const
{
    return "urma_1153";
}
} // namespace diag
