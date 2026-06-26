#include "urma_failure_347.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure347> g_urma("urma_347");

bool UrmaFailure347::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_seg_cfg") != std::string::npos &&
           message.find("token_id must set when token_id_valid is true, or must NULL when token_id_valid is false.") !=
               std::string::npos;
}

std::string UrmaFailure347::GetName() const
{
    return "Segment、CFG状态不满足要求导致校验Segment、CFG失败";
}

std::string UrmaFailure347::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg执行校验Segment、CFG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure347::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure347::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure347::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，token_id must set when token_id_valid is true, or "
           "must NUL"
           "L when token_id_valid is false.。";
}

std::string UrmaFailure347::GetId() const
{
    return "urma_347";
}
} // namespace diag
