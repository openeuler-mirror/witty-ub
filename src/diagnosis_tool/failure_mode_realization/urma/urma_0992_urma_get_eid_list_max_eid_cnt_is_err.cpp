#include "urma_0992_urma_get_eid_list_max_eid_cnt_is_err.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0992UrmaGetEidListMaxEidCntIsErr> g_urma("urma_0992");

bool Urma0992UrmaGetEidListMaxEidCntIsErr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"max eid cnt % is err"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0992UrmaGetEidListMaxEidCntIsErr::GetName() const
{
    return "urma_get_eid_list max eid cnt % is err";
}

std::string Urma0992UrmaGetEidListMaxEidCntIsErr::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `max_eid_cnt == 0`；该路径返回 NULL";
}

RootCause Urma0992UrmaGetEidListMaxEidCntIsErr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0992UrmaGetEidListMaxEidCntIsErr::GetFixSuggDesc() const
{
    return "```\nlsmod | grep udma\nurma_admin show -a // 查看UB设备是否存在，部署完成后重试\n```";
}

std::string Urma0992UrmaGetEidListMaxEidCntIsErr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：max eid cnt % is err";
}

std::string Urma0992UrmaGetEidListMaxEidCntIsErr::GetId() const
{
    return "urma_0992";
}
} // namespace diag
