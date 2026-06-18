#include "urma_failure_348.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure348> g_urma("urma_348");

bool UrmaFailure348::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_seg_cfg") != std::string::npos &&
           message.find("Local only access is not allowed to config with other accesses.") != std::string::npos;
}

std::string UrmaFailure348::GetName() const
{
    return "Segment、CFG状态不满足要求导致校验Segment、CFG失败";
}

std::string UrmaFailure348::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg执行校验Segment、CFG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure348::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure348::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure348::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，Local only access is not allowed to config with "
           "other acce"
           "sses.。";
}

std::string UrmaFailure348::GetId() const
{
    return "urma_348";
}
} // namespace diag
