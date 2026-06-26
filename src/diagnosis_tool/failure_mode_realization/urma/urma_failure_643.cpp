#include "urma_failure_643.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure643> g_urma("urma_643");

bool UrmaFailure643::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_seg_cfg") != std::string::npos &&
           message.find("Write access should be config with read access.") != std::string::npos;
}

std::string UrmaFailure643::GetName() const
{
    return "Segment、CFG状态不满足要求导致校验Segment、CFG失败";
}

std::string UrmaFailure643::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg执行校验Segment、CFG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure643::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure643::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure643::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，Write access should be config with read access.。";
}

std::string UrmaFailure643::GetId() const
{
    return "urma_643";
}
} // namespace diag
