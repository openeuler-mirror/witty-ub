#include "urma_1158_urma_unregister_seg_segment_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1158UrmaUnregisterSegSegmentRegisterFailure> g_urma("urma_1158");

bool Urma1158UrmaUnregisterSegSegmentRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Unregister seg fail, dev_name: %, eid_idx: %, tid: %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1158UrmaUnregisterSegSegmentRegisterFailure::GetName() const
{
    return "urma_unregister_seg 注册Segment失败";
}

std::string Urma1158UrmaUnregisterSegSegmentRegisterFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求";
}

RootCause Urma1158UrmaUnregisterSegSegmentRegisterFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1158UrmaUnregisterSegSegmentRegisterFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1158UrmaUnregisterSegSegmentRegisterFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Unregister seg fail, dev_name: %, eid_idx: %, tid: %, "
           "ret: %.";
}

std::string Urma1158UrmaUnregisterSegSegmentRegisterFailure::GetId() const
{
    return "urma_1158";
}
} // namespace diag
