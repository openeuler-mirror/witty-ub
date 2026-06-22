#include "urma_failure_644.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure644> g_urma("urma_644");

bool UrmaFailure644::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_seg_cfg") != std::string::npos &&
           message.find("Atomic access should be config with read and write access.") != std::string::npos;
}

std::string UrmaFailure644::GetName() const
{
    return "Segment、CFG状态不满足要求导致校验Segment、CFG失败";
}

std::string UrmaFailure644::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg执行校验Segment、CFG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure644::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure644::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure644::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，Atomic access should be config with read and write "
           "access."
           "。";
}

std::string UrmaFailure644::GetId() const
{
    return "urma_644";
}
} // namespace diag
