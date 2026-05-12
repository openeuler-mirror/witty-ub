#include "urma_1030_urma_alloc_token_id_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1030UrmaAllocTokenIdSegmentRegisterFailure> g_urma("urma_1030");

bool Urma1030UrmaAllocTokenIdSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to register seg, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1030UrmaAllocTokenIdSegmentRegisterFailure::GetName() const
{
    return "urma_alloc_token_id 注册Segment失败";
}

std::string Urma1030UrmaAllocTokenIdSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 "
           "token_id";
}

RootCause Urma1030UrmaAllocTokenIdSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1030UrmaAllocTokenIdSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1030UrmaAllocTokenIdSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to register seg, dev_name: %, eid_idx: %.";
}

std::string Urma1030UrmaAllocTokenIdSegmentRegisterFailure::GetId() const
{
    return "urma_1030";
}
} // namespace diag
