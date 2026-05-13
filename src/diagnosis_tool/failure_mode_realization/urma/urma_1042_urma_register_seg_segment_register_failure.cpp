#include "urma_1042_urma_register_seg_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1042UrmaRegisterSegSegmentRegisterFailure> g_urma("urma_1042");

bool Urma1042UrmaRegisterSegSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]register seg failed, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1042UrmaRegisterSegSegmentRegisterFailure::GetName() const
{
    return "urma_register_seg 注册Segment失败";
}

std::string Urma1042UrmaRegisterSegSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 NULL";
}

RootCause Urma1042UrmaRegisterSegSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1042UrmaRegisterSegSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1042UrmaRegisterSegSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]register seg failed, dev_name: %, eid_idx: %.";
}

std::string Urma1042UrmaRegisterSegSegmentRegisterFailure::GetId() const
{
    return "urma_1042";
}
} // namespace diag
